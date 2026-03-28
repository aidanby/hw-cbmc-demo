// Simplified I2C master controller.
//
// Sends START condition, 8-bit address MSB-first, waits for ACK from slave.
// Uses open-drain outputs: oe=1 means DRIVE LINE LOW, oe=0 means RELEASE
// (external pull-up brings line HIGH).
//
// FSM: IDLE(0) -> START(1) -> SEND(2, 8 bits) -> ACK(3) -> DONE(4) -> IDLE
// Each bit-state has two phases: phase=0 (SCL low, setup data on SDA),
//                                 phase=1 (SCL high, hold/sample data).
//
// Three bugs corrupt the SDA polarity, bit ordering, and ACK detection.
module i2c_master(
  input  clk,
  input  reset,
  input  go,
  input  [7:0] addr,
  output reg scl_oe,
  output reg sda_oe,
  input  sda_in,
  output reg done,
  output reg ack_ok
);
  localparam IDLE  = 3'd0;
  localparam START = 3'd1;
  localparam SEND  = 3'd2;
  localparam ACK   = 3'd3;
  localparam DONE_ST = 3'd4;

  reg [2:0] state;
  reg [2:0] bit_idx;
  reg [7:0] addr_reg;
  reg       phase;

  initial begin
    state = IDLE; bit_idx = 3'd6; addr_reg = 0; phase = 0;
    scl_oe = 0; sda_oe = 0; done = 0; ack_ok = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      state    <= IDLE;
      bit_idx  <= 3'd6;
      addr_reg <= 8'd0;
      phase    <= 1'b0;
      scl_oe   <= 1'b0;
      sda_oe   <= 1'b0;
      done     <= 1'b0;
      ack_ok   <= 1'b0;
    end else begin
      case (state)
        IDLE: begin
          scl_oe <= 1'b0;   // Release SCL (HIGH)
          sda_oe <= 1'b0;   // Release SDA (HIGH)
          done   <= 1'b0;
          if (go) begin
            addr_reg <= addr;
            state    <= START;
            phase    <= 1'b0;
          end
        end

        START: begin
          // START condition: SDA goes LOW while SCL is HIGH
          if (phase == 1'b0) begin
            scl_oe <= 1'b0;  // SCL released (HIGH)
            sda_oe <= 1'b1;  // SDA driven LOW (start condition)
            phase  <= 1'b1;
          end else begin
            scl_oe <= 1'b1;  // SCL driven LOW (prepare for first data bit)
            phase  <= 1'b0;
            bit_idx <= 3'd7;
            state   <= SEND;
          end
        end

        SEND: begin
          if (phase == 1'b0) begin
            // SCL LOW: setup SDA with data bit
            scl_oe <= 1'b0;                    // SCL driven LOW
            sda_oe <= ~addr_reg[bit_idx + 1];
            phase  <= 1'b1;
          end else begin
            // SCL HIGH: hold data
            scl_oe <= 1'b0;                    // SCL released (HIGH)
            phase  <= 1'b0;
            bit_idx <= bit_idx - 3'd2;
            if (bit_idx == 3'd0)
              state <= ACK;
          end
        end

        ACK: begin
          if (phase == 1'b0) begin
            scl_oe <= 1'b1;   // SCL LOW
            sda_oe <= 1'b0;   // Release SDA (slave drives it)
            phase  <= 1'b1;
          end else begin
            scl_oe  <= 1'b0;  // SCL HIGH: sample ACK
            ack_ok  <= ~addr_reg[0];
            phase   <= 1'b0;
            state   <= DONE_ST;
          end
        end

        DONE_ST: begin
          scl_oe <= 1'b0;
          sda_oe <= 1'b0;
          done   <= 1'b1;
          state  <= IDLE;
        end
      endcase
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> state == IDLE && !done);
  p_done_pulse: assert property (@(posedge clk) done |=> !done || reset);
  p_send_0:     assert property (@(posedge clk) !reset && state == SEND && phase == 1'b0 && addr_reg[bit_idx] == 1'b0 |=> reset || sda_oe == 1'b1);
  p_send_1:     assert property (@(posedge clk) !reset && state == SEND && phase == 1'b0 && addr_reg[bit_idx] == 1'b1 |=> reset || sda_oe == 1'b0);
  p_msb_order:  assert property (@(posedge clk) !reset && state == SEND && phase == 1'b1 && bit_idx > 3'd0 |=> bit_idx == ($past(bit_idx) - 3'd1));
  p_ack_sense:  assert property (@(posedge clk) !reset && state == ACK && phase == 1'b1 && sda_in == 1'b0 |=> ack_ok == 1'b1);
endmodule
