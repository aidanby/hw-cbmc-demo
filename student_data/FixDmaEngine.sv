// 2-channel DMA engine with round-robin bus arbitration.
//
// Each channel has: src_addr, len (transfer count), go (start), active flag.
// The engine transfers one word per cycle from the active channel, decrementing
// len and incrementing src_addr until len reaches 0.
//
// Arbitration: when both channels request, alternate between them (round-robin
// via turn register). A channel retains the bus until it completes unless the
// other channel also needs it.
//
// Three bugs corrupt the address generation, the completion detection,
// and the turn arbitration feedback.
module dma_engine(
  input        clk,
  input        reset,
  // Channel 0
  input        go0,
  input  [7:0] src0,
  input  [3:0] len0,
  // Channel 1
  input        go1,
  input  [7:0] src1,
  input  [3:0] len1,
  // Bus output
  output reg [7:0] bus_addr,
  output reg       bus_req,
  output reg       ch0_done,
  output reg       ch1_done
);
  // Channel state
  reg       active0, active1;
  reg [7:0] addr0, addr1;
  reg [3:0] rem0, rem1;         // remaining transfer count
  reg       turn;               // 0=ch0 priority, 1=ch1 priority

  initial begin
    active0 = 0; active1 = 0;
    addr0 = 0; addr1 = 0;
    rem0 = 0; rem1 = 0;
    turn = 0;
    bus_addr = 0; bus_req = 0;
    ch0_done = 0; ch1_done = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      active0 <= 0; active1 <= 0;
      addr0 <= 0; addr1 <= 0;
      rem0 <= 0; rem1 <= 0;
      turn <= 0;
      bus_addr <= 0; bus_req <= 0;
      ch0_done <= 0; ch1_done <= 0;
    end else begin
      ch0_done <= 1'b0;
      ch1_done <= 1'b0;
      bus_req  <= 1'b0;

      // ── Channel activation ──
      if (go0 && !active0) begin
        active0 <= 1'b1;
        addr0   <= src0;
        rem0    <= len0;
      end
      if (go1 && !active1) begin
        active1 <= 1'b1;
        addr1   <= src1;
        rem1    <= len1;
      end

      // ── Bus arbitration + transfer ──
      if (active0 && active1) begin
        // Both active: use turn to decide
        if (turn == 1'b0) begin
          // Channel 0 gets bus
          bus_addr <= addr0;
          bus_req  <= 1'b1;
          addr0    <= addr1 + 8'd1; // HINT: check this line carefully
          rem0     <= rem0 - 4'd1;
          if (rem0 == 4'd1) begin
            active0  <= 1'b0;
            ch0_done <= 1'b1;
          end
          turn <= 1'b0; // HINT: check this line carefully
        end else begin
          // Channel 1 gets bus
          bus_addr <= addr1;
          bus_req  <= 1'b1;
          addr1    <= addr1 + 8'd1;
          rem1     <= rem1 - 4'd1;
          if (rem1 == 4'd1) begin
            active1  <= 1'b0;
            ch1_done <= 1'b1;
          end
          turn <= 1'b0;
        end
      end else if (active0) begin
        bus_addr <= addr0;
        bus_req  <= 1'b1;
        addr0    <= addr0 + 8'd1;
        rem0     <= rem0 - 4'd1;
        if (rem0 == 4'd15) begin
          active0  <= 1'b0;
          ch0_done <= 1'b1;
        end
      end else if (active1) begin
        bus_addr <= addr1;
        bus_req  <= 1'b1;
        addr1    <= addr1 + 8'd1;
        rem1     <= rem1 - 4'd1;
        if (rem1 == 4'd15) begin
          active1  <= 1'b0;
          ch1_done <= 1'b1;
        end
      end
    end
  end

  // Properties
  p_reset:      assert property (@(posedge clk) reset |=> !bus_req && !ch0_done && !ch1_done);
  p_addr0_inc:  assert property (@(posedge clk) !reset && active0 && bus_req && bus_addr == addr0 |=> addr0 == ($past(addr0) + 8'd1));
  p_ch0_done:   assert property (@(posedge clk) !reset && active0 && rem0 == 4'd1 && bus_addr == addr0 && bus_req |=> ch0_done);
  p_ch1_done:   assert property (@(posedge clk) !reset && active1 && rem1 == 4'd1 && bus_addr == addr1 && bus_req |=> ch1_done);
  p_turn_flip:  assert property (@(posedge clk) !reset && active0 && active1 && turn == 1'b0 && bus_req |=> turn == 1'b1);
  p_no_starve:  assert property (@(posedge clk) !reset && active0 && active1 && turn == 1'b1 |=> bus_addr == $past(addr1));
  p_mutex:      assert property (@(posedge clk) !(ch0_done && ch1_done));
endmodule
