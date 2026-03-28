// SPI slave — mode 0 (CPOL=0, CPHA=0).
// Samples MOSI on the RISING edge of SCLK.
// Receives 8 bits MSB-first. Pulses data_valid for exactly 1 system clock
// after the 8th SCLK rising edge. CS (cs_n) is active-low.
// CS de-assert or reset clears the in-progress frame.
//
// Three bugs cause wrong byte values and incorrect framing.
module spi_slave(
  input  clk,       // system clock (runs faster than SCLK)
  input  reset,
  input  cs_n,      // chip-select, active-low
  input  sclk,      // SPI clock from master
  input  mosi,
  output reg [7:0] rx_data,
  output reg       data_valid
);
  reg       sclk_d;
  reg [7:0] shift;
  reg [2:0] bit_cnt;  // counts 0..7; fires valid when this rolls from 7 back to 0

  always @(posedge clk) begin
    if (reset || cs_n) begin
      sclk_d     <= 1'b0;
      shift      <= 8'h00;
      bit_cnt    <= 3'd0;
      data_valid <= 1'b0;
      rx_data    <= 8'h00;
    end else begin
      data_valid <= 1'b0;
      sclk_d     <= sclk;

      if (!sclk_d && sclk) begin        // rising SCLK edge
        // Bug 1: shift direction wrong — should be MSB-first: {mosi, shift[7:1]}
        shift   <= {shift[6:0], mosi};  // BUG: LSB-first accumulation
        bit_cnt <= bit_cnt + 1;

        if (bit_cnt == 3'd7) begin
          // Bug 2: capture should use MSB-first expression {mosi, shift[7:1]}
          rx_data    <= {shift[6:0], mosi};  // BUG: captures LSB-first byte
          data_valid <= 1'b1;
          bit_cnt    <= 3'd0;
        end
      end
    end
  end

  // Bug 3: CS de-assert during transfer must reset bit_cnt.
  // The current code resets on cs_n=1 (covered by the outer if), BUT:
  // when CS goes low again, bit_cnt starts from whatever value it had —
  // it is NOT guaranteed to be 0 if CS pulsed mid-transfer.
  // Fix: bit_cnt must reset to 0 whenever cs_n rises (cs_n transitions 0→1).
  // Currently: bit_cnt is reset ONLY when cs_n is already high (combinational),
  // so if cs_n pulses for just one clock then goes low again, bit_cnt
  // picks up mid-stream from the latched reset value.
  // (Hint: add a registered cs_n_d signal and check for cs_n rising edge.)

  p_reset:   assert property (@(posedge clk) (reset || cs_n) |=> !data_valid && bit_cnt == 3'd0);
  p_one_cyc: assert property (@(posedge clk) data_valid |=> !data_valid || cs_n);
  p_byte:    assert property (@(posedge clk) data_valid && $past(shift) == 8'hA5 |-> rx_data == 8'hA5);
  p_msb:     assert property (@(posedge clk) !cs_n && !$past(cs_n) && !sclk_d && sclk
                               && bit_cnt == 3'd0 && mosi == 1'b1 |=> shift[7] == 1'b1);
endmodule
