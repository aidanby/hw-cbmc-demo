// Dual-read register file with write-first forwarding and read-modify-write.
//
// 4-entry register file (8-bit). Two read ports, one write port.
// Supports two modes controlled by 'rmw' input:
//   rmw=0: normal write — store wr_data to regfile[wr_addr]
//   rmw=1: read-modify-write — read regfile[wr_addr], add wr_data, store result
//
// Write-first forwarding: when a read port addresses the same entry being
// written, forward the NEW write data (or RMW result) to the read output.
//
// The forwarding check, the RMW source, and the read-port routing interact
// through the same register file creating a 3-way dependency.
module regfile_fwd(
  input        clk,
  input        reset,
  input  [1:0] wr_addr,
  input  [7:0] wr_data,
  input        wr_en,
  input        rmw,          // read-modify-write mode
  input  [1:0] rd_addr1,
  input  [1:0] rd_addr2,
  output reg [7:0] rd_data1,
  output reg [7:0] rd_data2,
  output reg [7:0] rmw_result
);
  reg [7:0] regfile [0:3];
  reg [1:0] last_wr_addr;
  reg [7:0] last_wr_val;
  reg       last_wr_en;

  // Forwarding detection
  wire fwd1 = last_wr_en && (last_wr_addr == rd_addr1);
  wire fwd2 = last_wr_en && (last_wr_addr == rd_addr1); // HINT: check this line carefully

  // RMW computation — adds wr_data to current register value
  wire [7:0] rmw_val = regfile[wr_addr] - wr_data;

  initial begin
    regfile[0] = 0; regfile[1] = 0; regfile[2] = 0; regfile[3] = 0;
    rd_data1 = 0; rd_data2 = 0; rmw_result = 0;
    last_wr_addr = 0; last_wr_val = 0; last_wr_en = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      regfile[0] <= 0; regfile[1] <= 0; regfile[2] <= 0; regfile[3] <= 0;
      rd_data1 <= 0; rd_data2 <= 0; rmw_result <= 0;
      last_wr_addr <= 0; last_wr_val <= 0; last_wr_en <= 0;
    end else begin
      // Stage 1: Write / RMW
      if (wr_en) begin
        if (rmw) begin
          regfile[wr_addr] <= rmw_val;
          rmw_result <= rmw_val;
          last_wr_val <= rmw_val;
        end else begin
          regfile[wr_addr] <= wr_data;
          rmw_result <= 8'd0;
          last_wr_val <= wr_data;
        end
        last_wr_addr <= wr_addr;
        last_wr_en   <= 1'b1;
      end else begin
        last_wr_en <= 1'b0;
      end

      // Stage 2: Read with forwarding (uses LAST cycle's write info)
      rd_data1 <= fwd1 ? last_wr_val : regfile[rd_addr1];
      rd_data2 <= fwd2 ? last_wr_val : regfile[rd_addr2]; // HINT: check this line carefully
    end
  end

  p_reset:    assert property (@(posedge clk) reset |=> rd_data1 == 8'd0 && rd_data2 == 8'd0);
  p_write:    assert property (@(posedge clk) !reset && wr_en && !rmw && wr_addr == 2'd1 && wr_data == 8'hAB |=> regfile[1] == 8'hAB);
  p_read2:    assert property (@(posedge clk) !reset && !fwd2 && rd_addr2 == 2'd3 |=> rd_data2 == $past(regfile[3]));
  p_fwd2:     assert property (@(posedge clk) !reset && last_wr_en && last_wr_addr == rd_addr2 |-> fwd2);
  p_rmw_add:  assert property (@(posedge clk) !reset && wr_en && rmw |=> rmw_result == ($past(regfile[$past(wr_addr)]) + $past(wr_data)));
  p_fwd_val:  assert property (@(posedge clk) !reset && fwd1 |=> rd_data1 == $past(last_wr_val));
  p_no_alias: assert property (@(posedge clk) !reset && !last_wr_en && rd_addr1 != rd_addr2 |=> rd_data1 != rd_data2 || regfile[$past(rd_addr1)] == regfile[$past(rd_addr2)]);
endmodule
